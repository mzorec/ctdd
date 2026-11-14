namespace Shop.Application.UnitTests.Orders;

public sealed class SetOrderStateHandlerTests
{
    [Fact]
    public async Task Handle_ReturnsConflict_WhenTheMoveIsNotAllowed()
    {
        var orders = new RecordingOrderRepository(OrderStateOutcome.NotAllowed);
        var command = new SetOrderStateCommand("A-400", SettableOrderState.Shipped, "late");

        var result = await new SetOrderStateCommandHandler(orders, NullLogger<SetOrderStateCommandHandler>.Instance)
            .Handle(command, CancellationToken.None);

        Assert.Equal(ResultStatus.Conflict, result.Status);
        Assert.Equal(OrderErrorCodes.StateChangeNotAllowed, result.ErrorCode);
        Assert.Equal(command.Note, orders.LastNote);
    }
}

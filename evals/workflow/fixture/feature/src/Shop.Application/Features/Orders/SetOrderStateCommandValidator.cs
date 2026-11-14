using FluentValidation;

namespace Shop.Application.Features.Orders;

public sealed class SetOrderStateCommandValidator : AbstractValidator<SetOrderStateCommand>
{
    public SetOrderStateCommandValidator()
    {
        RuleFor(x => x.OrderNumber).NotEmpty();
        RuleFor(x => x.Note).MaximumLength(500);
    }
}
